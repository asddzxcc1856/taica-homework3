package course.taica.hw3;

import org.apache.jena.rdf.model.InfModel;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.reasoner.Reasoner;
import org.apache.jena.reasoner.ReasonerRegistry;
import org.apache.jena.reasoner.ValidityReport;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.RDFFormat;

import java.io.FileOutputStream;
import java.util.Iterator;

/**
 * TAICA HW3 — Task 4 reasoning step (TA-provided, no student TODO here).
 *
 * Loads the ontology + the student's reasoning.ttl axioms + data.ttl,
 * binds Jena's OWL rule reasoner, and materializes the deductions:
 * membership of the inference-defined evaluation classes
 * (e.g. hw3:SolvedIKComputation) is DERIVED, never asserted.
 *
 * Usage:
 *   java course.taica.hw3.SemanticReasoner &lt;inferred_out.ttl&gt; &lt;in1.ttl&gt; [in2.ttl ...]
 */
public final class SemanticReasoner {

    private SemanticReasoner() { }

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("usage: SemanticReasoner <inferred_out.ttl> <in1.ttl> [in2.ttl ...]");
            System.exit(2);
        }
        Model data = ModelFactory.createDefaultModel();
        for (int i = 1; i < args.length; i++) {
            Model m = RDFDataMgr.loadModel(args[i]);
            data.add(m);
            data.setNsPrefixes(m);
            System.out.println("[LOAD] " + m.size() + " triples from " + args[i]);
        }

        Reasoner reasoner = ReasonerRegistry.getOWLReasoner();
        InfModel inf = ModelFactory.createInfModel(reasoner, data);

        ValidityReport validity = inf.validate();
        if (validity.isValid()) {
            System.out.println("[REASON] ontology + data are consistent");
        } else {
            System.out.println("[REASON] CONSISTENCY VIOLATIONS:");
            for (Iterator<ValidityReport.Report> it = validity.getReports(); it.hasNext(); ) {
                System.out.println("  - " + it.next());
            }
        }

        // Export the FULL inference model: serialization materializes the
        // derived memberships of the equivalence classes (the deductions
        // model alone misses results of the hybrid backward engine).
        Model export = ModelFactory.createDefaultModel();
        export.add(inf);
        export.setNsPrefixes(data);
        try (FileOutputStream out = new FileOutputStream(args[0])) {
            RDFDataMgr.write(out, export, RDFFormat.TURTLE_PRETTY);
        }
        System.out.println("[EXPORT] inferred graph (" + export.size()
                + " triples) written to " + args[0]);
    }
}
